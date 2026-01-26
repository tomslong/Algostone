import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Rocket, Lightbulb, Shield, Zap, Settings, Code2 } from 'lucide-react';

const HomePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Header */}
      <header className="border-b p-4 flex justify-between items-center px-8">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 bg-primary rounded-lg flex items-center justify-center">
            <Code2 className="text-primary-foreground h-5 w-5" />
          </div>
          <span className="font-bold text-xl">AlgoStone</span>
        </div>
        <div className="flex gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/settings')}>
            <Settings className="h-5 w-5" />
          </Button>
          <Button variant="ghost">Documentation</Button>
          <Button variant="ghost">Sign In</Button>
        </div>
      </header>

      {/* Hero Section */}
      <div className="flex-1 flex flex-col items-center justify-center py-20 px-4 text-center space-y-8 bg-muted/50">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
          AlgoStone 算法学习助手
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl">
          通过引导式对话，帮助你深度理解算法思维
        </p>
        <Button
          size="lg"
          onClick={() => navigate('/ide')}
          className="text-lg px-8 py-6 h-auto"
        >
          <Rocket className="mr-2 h-6 w-6" />
          开始学习
        </Button>
      </div>

      {/* Features Section */}
      <div className="py-20 px-4 md:px-8">
        <h2 className="text-3xl font-bold text-center mb-12">
          核心特色
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6 max-w-7xl mx-auto">
          <FeatureCard 
            icon={<Lightbulb className="h-10 w-10 text-yellow-500" />}
            title="智能引导"
            description="不直接给答案，通过提问引导你独立思考，培养算法思维"
          />
          <FeatureCard 
            icon={<Shield className="h-10 w-10 text-blue-500" />}
            title="安全沙盒"
            description="在隔离环境中执行代码，捕捉常见错误并提供中文解释"
          />
          <FeatureCard 
            icon={<Zap className="h-10 w-10 text-purple-500" />}
            title="RAG知识库"
            description="集成LeetCode经典题目，快速检索相关算法知识"
          />
          <FeatureCard 
            icon={<Rocket className="h-10 w-10 text-red-500" />}
            title="阶梯提示"
            description="从算法方向到伪代码，循序渐进地提供帮助"
          />
        </div>
      </div>
    </div>
  );
};

const FeatureCard = ({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) => (
  <Card className="hover:shadow-lg transition-shadow border-none shadow-md">
    <CardHeader className="flex flex-col items-center space-y-4 pb-2">
      <div className="p-3 bg-secondary/20 rounded-full text-foreground">
        {icon}
      </div>
      <CardTitle className="text-xl">{title}</CardTitle>
    </CardHeader>
    <CardContent className="text-center text-muted-foreground">
      {description}
    </CardContent>
  </Card>
);

export default HomePage;
